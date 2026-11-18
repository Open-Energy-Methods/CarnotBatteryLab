"""Matched-charge numerical study; no industrial service claim."""
import argparse,json
from dataclasses import replace
from pathlib import Path
from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle

def study():
    c=replace(ClosedCycle(),discharge_s=600.)
    cases={
        "forward":(c,False,2.,1),
        "reverse":(c,True,2.,1),
        "reverse_bed_refined":(replace(c,train=replace(c.train,bed_cells=5)),True,2.,1),
        "reverse_hx_refined":(replace(c,train=replace(c.train,hx_cells=5)),True,2.,1),
        "reverse_half_step":(replace(c,max_step_s=2.5),True,2.,1),
        "reverse_high_valve_loss":(c,True,20.,1),
        "forward_repeated":(c,False,2.,3),
        "reverse_repeated":(c,True,2.,3),
    }
    out={}
    for name,(cfg,rev,K,n) in cases.items():
        v=run_closed_cycle(cfg,reverse_discharge=rev,valve_loss_K=K,cycles=n)
        rows=[]
        for item in v["cycle_records"]:
            ch,di=item["charge"],item["discharge"]
            row=dict(cycle=item["cycle"],heater_electric_J=ch["heater_electric_J"],
                charge_blower_electric_J=ch["blower_electric_J"],
                discharge_blower_electric_J=di["blower_electric_J"],
                gross_signed_water_heat_J=di["water_boundary_heat_J"],
                qualified_heat_J=di["qualified_water_heat_J"],
                qualified_duration_s=di["qualified_water_duration_s"],
                final_water_C=di["final_water_outlet_C"],peak_water_C=di["max_water_outlet_C"],
                rock_state_change_K=item["max_rock_cycle_end_change_K"])
            rows.append(row)
        out[name]=dict(summary=rows,result=v)
        print(name,json.dumps(rows),flush=True)
    a,b=(out[n]["summary"][0] for n in ("forward","reverse"))
    return dict(research_stage="M3_11_REVERSE_FLOW_RECOVERY",results=out,
        matched_cold_start_charge_heater_difference_J=b["heater_electric_J"]-a["heater_electric_J"],
        matched_cold_start_charge_blower_difference_J=b["charge_blower_electric_J"]-a["charge_blower_electric_J"],
        reverse_minus_forward_qualified_heat_J=b["qualified_heat_J"]-a["qualified_heat_J"],
        reverse_minus_forward_qualified_duration_s=b["qualified_duration_s"]-a["qualified_duration_s"],
        hardware_qualified=False,experimental_validation=False,industrial_matched_service=False,Carnot_battery_RTE=None)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("results/m3_11_reverse_flow_recovery.json"))
    a=p.parse_args();x=study()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n")
