"""Fixed 1 MW service screen. No automatic optimization claim."""
import argparse,json
from dataclasses import replace
from pathlib import Path
from carnot_battery_lab.physics.thermal_retention import ThermalBuffer,buffer_periodic_gate,water_service_exergy
from carnot_battery_lab.physics.industrial_bank import equivalent_bank,staggered_loads

# n, max step, cooler cap, control threshold, heater MW, buffer enabled
CASES={
    "reference":(16,5.,1e6,None,5.,False),
    "cap0":(16,5.,0.,None,5.,False),
    "cap250k":(16,5.,250e3,None,5.,False),
    "cap500k":(16,5.,500e3,None,5.,False),
    "cap750k":(16,5.,750e3,None,5.,False),
    "cap1MW_n12":(12,5.,1e6,None,5.,False),
    "cap1MW_halfstep":(16,2.5,1e6,None,5.,False),
    "feedback_return_160C":(16,5.,1e6,433.15,5.,False),
    "feedback_return_170C":(16,5.,1e6,443.15,5.,False),
    "cap0_heater3MW":(16,5.,0.,None,3.,False),
    "cap500k_heater3MW":(16,5.,500e3,None,3.,False),
    "cap500k_buffer":(16,5.,500e3,None,5.,True),
    "cap0_buffer":(16,5.,0.,None,5.,True),
}

def run(name,*,cases=CASES,main_heat_loss=None):
    from CoolProp.CoolProp import PropsSI
    from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
    from carnot_battery_lab.physics.periodic_recovery import periodic_audit
    n,dt,cap,setpoint,heater,buffer=cases[name]
    base=ClosedCycle()
    base=replace(base,discharge_s=600.,max_step_s=dt,train=replace(base.train,bed_cells=n,hx_cells=n))
    c,g=equivalent_bank(base,modules=1000,vessels=20,header_diameter_m=4.)
    c=replace(c,heater_max_electric_W=heater*1e6)
    buf=ThermalBuffer(5e6,1e5,100.) if buffer else None
    v=run_closed_cycle(c,reverse_discharge=True,valve_loss_K=2.,cycles=10,process_duty_W=1e6,
                       cooler_cap_W=cap,cooler_control_K=setpoint,recuperator=buf,trace_interval_s=10.,main_heat_loss=main_heat_loss)
    for row in v["cycle_records"]:
        for phase in ("charge","discharge"):
            z=row[phase]
            assert abs(z["mass_residual_kg"])<1e-7
            assert max(abs(x) for x in z["component_thermal_residuals_J"].values())<10.
            assert abs(z["electrical_boundary_residual_J"])<10.
            assert z["peak_cooler_at_accepted_nodes_W"]<=cap+1e-8
            assert abs(z["recuperator_inventory_change_J"]-z["recuperator_captured_J"]+z["recuperator_returned_J"]+z["recuperator_ambient_loss_J"])<10.
            if phase=="charge":assert abs(z["recuperator_captured_J"])<1e-6
            else:assert abs(z["recuperator_returned_J"])<1e-6
        d=row["discharge"]
        assert abs(d["water_boundary_heat_J"]-(600e6-d["process_duty_deficit_J"]+d["process_duty_excess_J"]))<10.
        assert abs(d["water_throughput_kg"]-d["process_demand_flow_kg_s"]*600.)<1e-6
    assert abs(v["repeated_sequence_mass_residual_kg"])<1e-7
    assert abs(v["repeated_sequence_electrical_residual_J"])<50.
    audit=periodic_audit(v["cycle_records"])
    buffer_gate=buffer_periodic_gate(v["cycle_records"])
    loss_gate=True
    for prev,cur in zip(v["cycle_records"][-3:-1],v["cycle_records"][-2:]):
        for phase in ("charge","discharge"):
            for key in ("main_rock_ambient_heat_J","main_wall_ambient_heat_J","main_return_ambient_heat_J"):
                aa,bb=prev[phase][key],cur[phase][key]
                loss_gate=loss_gate and abs(aa-bb)<=max(10.,.005*max(abs(aa),abs(bb)))
    periodic=bool(audit["approximate_periodic_model_gate_pass"] and buffer_gate and loss_gate)
    row=v["cycle_records"][-1];ch=row["charge"].copy();d=row["discharge"]
    ch["assumed_heater_nameplate_W"]=c.heater_max_electric_W
    sched=staggered_loads(ch,d,1e6)
    full=bool(periodic and d["simultaneous_target_duration_s"]>=599.999999 and
        d["min_delivered_duty_W"]>=998500. and d["max_delivered_duty_W"]<=1001500. and
        d["min_water_outlet_C"]>=149.5 and d["max_water_outlet_C"]<=150.5)
    peak=max(z[k] for z in (ch,d) for k in ("peak_gas_temperature_at_accepted_nodes_K","peak_rock_temperature_at_accepted_nodes_K","peak_wall_temperature_at_accepted_nodes_K"))
    # Research-only, no material rating: no accepted node above 200 C.
    thermal_gate=peak<=473.15
    P=c.train.water_pressure_assumed_Pa;Tin=c.train.water_inlet_K;Tout=423.15
    h1,h2=[PropsSI("Hmass","T",T,"P",P,"Water") for T in (Tin,Tout)]
    s1,s2=[PropsSI("Smass","T",T,"P",P,"Water") for T in (Tin,Tout)]
    # Target reference only (no actual-flow exergy claimed for partial service).
    Btarget=water_service_exergy(600e6/(h2-h1),h1,h2,s1,s2)
    summary=dict(case=name,cells=n,max_step_s=dt,cooler_cap_W=cap,cooler_control_K=setpoint,heater_per_bank_MW=heater,buffer_enabled=buffer,
        periodic=periodic,buffer_periodic=buffer_gate,main_loss_periodic=loss_gate,full=full,thermal_gate=thermal_gate,
        main_heat_loss_assumptions=v['main_heat_loss_assumptions'],
        main_heat_loss_J=ch['main_ambient_heat_J']+d['main_ambient_heat_J'],
        main_rock_loss_J=ch['main_rock_ambient_heat_J']+d['main_rock_ambient_heat_J'],
        main_wall_loss_J=ch['main_wall_ambient_heat_J']+d['main_wall_ambient_heat_J'],
        main_return_loss_J=ch['main_return_ambient_heat_J']+d['main_return_ambient_heat_J'],
        eligible=bool(full and thermal_gate and d["min_hx_water_outlet_at_accepted_nodes_C"]>=150.),
        matched_s=d["simultaneous_target_duration_s"],deficit_J=d["process_duty_deficit_J"],
        raw_margin_K=d["min_hx_water_outlet_at_accepted_nodes_C"]-150.,
        peak_thermal_K=peak,mean_electric_W=sched["mean_modeled_electric_W"],
        sampled_peak_electric_W=sched["sampled_peak_electric_W"],installed_heater_W=sched["installed_heater_W"],
        cooler_J=d["cooler_heat_to_assumed_sink_J"],peak_cooler_W=d["peak_cooler_at_accepted_nodes_W"],
        captured_J=d["recuperator_captured_J"],returned_J=ch["recuperator_returned_J"],
        buffer_loss_J=ch["recuperator_ambient_loss_J"]+d["recuperator_ambient_loss_J"],
        buffer_inventory_drift_J=ch["recuperator_inventory_change_J"]+d["recuperator_inventory_change_J"],
        buffer_end_K=d["recuperator_end_K"],requested_service_exergy_J=Btarget,
        target_exergy_per_modeled_electric=Btarget/sched["modeled_electric_per_slot_J"] if full else None,
        hardware_qualified=False,continuous_service_qualified=False)
    print(json.dumps(summary),flush=True)
    return dict(summary=summary,result=v,schedule=sched,audit=audit,geometry=g)

def aggregate(root):
    cases={}
    for p in root.rglob("case_*.json"):
        v=json.loads(p.read_text());s=v["summary"];k=s["case"]
        if k in cases or k not in CASES:raise ValueError("duplicate or unknown case")
        if (s["cells"],s["max_step_s"],s["cooler_cap_W"],s["cooler_control_K"],s["heater_per_bank_MW"],s["buffer_enabled"])!=CASES[k]:raise ValueError("case mismatch")
        cases[k]=s
    if set(cases)!=set(CASES):raise ValueError("incomplete study")
    ref=cases["reference"]
    assert ref["full"] and abs(ref["mean_electric_W"]-2114886.5575723182)/2114886.5575723182<.005
    eligible=[s for s in cases.values() if s["eligible"] and s["cells"]==16 and s["max_step_s"]==5.]
    best=min(eligible,key=lambda s:s["mean_electric_W"])["case"] if eligible else None
    sens={}
    for k in ("cap1MW_n12","cap1MW_halfstep"):
        s=cases[k]
        sens[k]=dict(both_eligible=ref["eligible"] and s["eligible"],
            electric_rel=abs(s["mean_electric_W"]-ref["mean_electric_W"])/ref["mean_electric_W"],
            raw_margin_K=abs(s["raw_margin_K"]-ref["raw_margin_K"]),
            peak_thermal_K=abs(s["peak_thermal_K"]-ref["peak_thermal_K"]))
    pairs={}
    for k,base in (("cap500k_buffer","cap500k"),("cap0_buffer","cap0")):
        a,b=cases[k],cases[base]
        pairs[k]=dict(baseline=base,both_eligible=a["eligible"] and b["eligible"],
            electric_difference_W=a["mean_electric_W"]-b["mean_electric_W"],
            returned_heat_J=a["returned_J"],capture_heat_J=a["captured_J"],
            no_credit_subtracted_from_electricity=True)
    x=dict(cases=cases,best_screened_case=best,reference_sensitivity=sens,buffer_comparisons=pairs,
        best_not_independently_refined=best not in (None,"reference"),component_exergy_balance_complete=False,
        hardware_qualified=False,industrial_service_qualified=False,Carnot_battery_RTE=None)
    print(json.dumps(x),flush=True);return x

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--case",choices=CASES);p.add_argument("--aggregate",type=Path)
    p.add_argument("--output",required=True,type=Path);a=p.parse_args()
    if bool(a.case)==bool(a.aggregate):p.error("select one mode")
    x=run(a.case) if a.case else aggregate(a.aggregate)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(x,indent=2,allow_nan=False)+"\n")
