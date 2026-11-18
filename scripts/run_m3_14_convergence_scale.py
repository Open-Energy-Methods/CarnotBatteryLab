import json
from dataclasses import replace
from pathlib import Path
from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
from carnot_battery_lab.physics.periodic_recovery import periodic_audit
from carnot_battery_lab.physics.scale_screen import convergence,module_screen

def study():
    base=replace(ClosedCycle(),discharge_s=600.)
    cases={}
    def run(name,duty,nb,nh,dt):
        cfg=replace(base,max_step_s=dt,train=replace(base.train,bed_cells=nb,hx_cells=nh))
        v=run_closed_cycle(cfg,reverse_discharge=True,valve_loss_K=2.,cycles=10,process_duty_W=duty)
        ch,d=v["cycle_records"][-1]["charge"],v["cycle_records"][-1]["discharge"]
        periodic=periodic_audit(v["cycle_records"])["approximate_periodic_model_gate_pass"]
        full=periodic and d["simultaneous_target_duration_s"]>=599.999999 and d["min_delivered_duty_W"]>=.9985*duty and d["max_delivered_duty_W"]<=1.0015*duty and d["min_water_outlet_C"]>=149.5 and d["max_water_outlet_C"]<=150.5
        assert abs(v["repeated_sequence_electrical_residual_J"])<.2
        assert abs(v["repeated_sequence_mass_residual_kg"])<1e-8
        result=dict(duty_W=duty,bed_cells=nb,hx_cells=nh,max_step_s=dt,periodic=periodic,full=full,
            deficit_J=d["process_duty_deficit_J"],matched_seconds=d["simultaneous_target_duration_s"],
            final_C=d["final_water_outlet_C"],delivered_J=d["water_boundary_heat_J"],
            min_duty_W=d["min_delivered_duty_W"],electric_J=ch["heater_electric_J"]+ch["blower_electric_J"]+d["blower_electric_J"],
            cooler_J=d["cooler_heat_to_assumed_sink_J"],water_flow=d["process_demand_flow_kg_s"])
        cases[name]=result
        print(name,json.dumps(result),flush=True)
        return result
    for q in (500,600,700,800,900,1000):
        run("envelope_"+str(q),q,3,3,5.)
    # Independently refine each spatial axis at fixed other axis, and time at fixed mesh.
    groups={}
    for axis in ("bed","hx","time","joint"):
        names=[]
        for level in (0,1,2):
            n=3*2**level
            nb=n if axis in ("bed","joint") else 3
            nh=n if axis in ("hx","joint") else 3
            dt=5./2**level if axis=="time" else 5.
            name=f"{axis}_{level}"
            run(name,1000.,nb,nh,dt);names.append(name)
        groups[axis]={k:convergence([cases[n][k] for n in names]) for k in ("deficit_J","matched_seconds","final_C","electric_J")}
        groups[axis]["all_periodic"]=all(cases[n]["periodic"] for n in names)
    passes=[v for k,v in cases.items() if k.startswith("envelope") and v["full"]]
    scale=None
    if passes:
        v=max(passes,key=lambda x:x["duty_W"])
        scale=module_screen(v["duty_W"],v["duty_W"]/v["water_flow"],v["electric_J"],v["cooler_J"])
        scale["basis"]="coarse-grid screened duty; not mesh-qualified"
        scale["bed_bulk_volume_m3"]=scale["parallel_modules"]*3.141592653589793*.3**2/4*.5
        scale["rock_mass_kg"]=scale["bed_bulk_volume_m3"]*.6*2600.
        scale["hx_UA_W_K"]=scale["parallel_modules"]*120.
        scale["installed_module_heater_W"]=scale["parallel_modules"]*5000.
    return dict(cases=cases,convergence=groups,scale=scale,hardware_qualified=False)
if __name__=="__main__":
    p=Path("results/m3_14_convergence_scale.json");p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(study(),indent=2,allow_nan=False)+"\n")
