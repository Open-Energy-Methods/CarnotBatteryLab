"""Run one expensive case per CI matrix job; aggregate only complete evidence."""
import argparse,json
from pathlib import Path
from dataclasses import replace
from carnot_battery_lab.physics.fine_duty_audit import compare_pair,size_candidate

CASES={f"q{q}_n{n}":(q,n,5.) for q in (500,1000,1250) for n in (12,16)}
CASES["q1000_n12_halfstep"]=(1000,12,2.5)

def run(case):
    from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
    from carnot_battery_lab.physics.periodic_recovery import periodic_audit
    duty,n,dt=CASES[case]
    base=ClosedCycle()
    c=replace(base,discharge_s=600.,max_step_s=dt,train=replace(base.train,bed_cells=n,hx_cells=n))
    v=run_closed_cycle(c,reverse_discharge=True,valve_loss_K=2.,cycles=10,process_duty_W=float(duty))
    audit=periodic_audit(v["cycle_records"])
    for row in v["cycle_records"]:
        ch,d=row["charge"],row["discharge"]
        assert abs(d["water_throughput_kg"]-d["process_demand_flow_kg_s"]*600.)<1e-6
        assert abs(d["water_boundary_heat_J"]-(duty*600.-d["process_duty_deficit_J"]+d["process_duty_excess_J"]))<.2
        assert 0<=d["simultaneous_target_duration_s"]<=600.
        for z in (ch,d):
            assert max(abs(x) for x in z["component_thermal_residuals_J"].values())<.2
            assert z["peak_cooler_at_accepted_nodes_W"]*z["duration_s"]>=z["cooler_heat_to_assumed_sink_J"]-.2
    assert abs(v["repeated_sequence_mass_residual_kg"])<1e-8
    assert abs(v["repeated_sequence_electrical_residual_J"])<.2
    ch,d=v["cycle_records"][-1]["charge"],v["cycle_records"][-1]["discharge"]
    periodic=audit["approximate_periodic_model_gate_pass"]
    full=bool(periodic and d["simultaneous_target_duration_s"]>=599.999999
        and d["min_delivered_duty_W"]>=.9985*duty and d["max_delivered_duty_W"]<=1.0015*duty
        and d["min_water_outlet_C"]>=149.5 and d["max_water_outlet_C"]<=150.5)
    summary=dict(case=case,duty_W=duty,cells=n,step_s=dt,periodic=periodic,full=full,
        raw_margin_K=d["min_hx_water_outlet_at_accepted_nodes_C"]-150.,
        matched_s=d["simultaneous_target_duration_s"],deficit_J=d["process_duty_deficit_J"],
        final_C=d["final_water_outlet_C"],water_flow=d["process_demand_flow_kg_s"],
        electric_J=ch["heater_electric_J"]+ch["blower_electric_J"]+d["blower_electric_J"],
        cooler_J=d["cooler_heat_to_assumed_sink_J"],peak_cooler_W=d["peak_cooler_at_accepted_nodes_W"],
        peak_blower_electric_W=max(z["peak_blower_electric_at_accepted_nodes_W"] for z in (ch,d)),
        peak_blower_flow_kg_s=max(z["peak_blower_flow_at_accepted_nodes_kg_s"] for z in (ch,d)),
        peak_heater_electric_W=ch["peak_heater_electric_at_accepted_nodes_W"])
    print(json.dumps(summary),flush=True)
    return dict(summary=summary,periodic_audit=audit,result=v)

def aggregate(root):
    v={}
    for p in root.rglob("case_*.json"):
        x=json.loads(p.read_text())
        s=x["summary"];key=s["case"]
        if key in v or key not in CASES:raise ValueError("duplicate or unknown result")
        if (s["duty_W"],s["cells"],s["step_s"])!=CASES[key]:raise ValueError("case mismatch")
        v[key]=s
    if set(v)!=set(CASES):raise ValueError("incomplete campaign")
    pairs={str(q):compare_pair(v[f"q{q}_n12"],v[f"q{q}_n16"]) for q in (500,1000,1250)}
    a,b=v["q1000_n12"],v["q1000_n12_halfstep"]
    temporal=dict(electric_relative_difference=abs(a["electric_J"]-b["electric_J"])/b["electric_J"],
                  raw_margin_difference_K=abs(a["raw_margin_K"]-b["raw_margin_K"]),
                  same_full_gate=a["full"]==b["full"],both_periodic=a["periodic"] and b["periodic"])
    temporal["screening_pass"]=bool(a["full"] and b["full"] and temporal["both_periodic"]
        and temporal["electric_relative_difference"]<=.02 and temporal["raw_margin_difference_K"]<=1.
        and b["raw_margin_K"]>=0)
    passing=[int(q) for q,p in pairs.items() if p["screening_pass"] and (q!="1000" or temporal["screening_pass"])]
    result=dict(cases=v,pairs=pairs,highest_discrete_two_grid_screened_W=max(passing) if passing else None,
                temporal_diagnostic_1000W=temporal,temporal_screening_other_duties_performed=False,
                scale=size_candidate(v[f"q{max(passing)}_n16"]) if passing else None,
                hardware_qualified=False,industrial_service_qualified=False,asymptotic_grid_convergence_established=False)
    print(json.dumps(result),flush=True)
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--case",choices=CASES)
    p.add_argument("--aggregate",type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    if bool(a.case)==bool(a.aggregate):p.error("select exactly one mode")
    x=run(a.case) if a.case else aggregate(a.aggregate)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(x,indent=2,allow_nan=False)+"\n")
