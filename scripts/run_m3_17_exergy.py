"""Matched-service physical exergy screen, real-air + liquid-water EOS.

No heat-pump compressor map, global optimisation or complete irreversibility
attribution is implied. Cases run independently on CI matrix.
"""
import argparse,json,math
from dataclasses import replace
from pathlib import Path
from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
from carnot_battery_lab.physics.industrial_bank import equivalent_bank,staggered_loads
from carnot_battery_lab.physics.periodic_recovery import periodic_audit
from carnot_battery_lab.physics.thermal_retention import MainHeatLoss

# cells, max-step seconds, heater nameplate MW per bank, main UA W/K, cooler W
CASES={
    "h3_adia_n16":(16,5.,3.,0.,0.),
    "h5_adia_n16":(16,5.,5.,0.,0.),
    "h3_loss100_n16":(16,5.,3.,100.,0.),
    "h3_loss500_n16":(16,5.,3.,500.,0.),
    "h3_loss1000_n16":(16,5.,3.,1000.,0.),
    "h3_loss500_n12":(12,5.,3.,500.,0.),
    "h3_loss500_halfstep":(16,2.5,3.,500.,0.),
    "h3_cooler1MW_n16":(16,5.,3.,0.,1e6),
}

def run_case(case):
    cells,step,heater,UA,cooler=CASES[case]
    base=ClosedCycle()
    base=replace(base,discharge_s=600.,max_step_s=step,
        train=replace(base.train,bed_cells=cells,hx_cells=cells))
    cfg,geometry=equivalent_bank(base,modules=1000,vessels=20,header_diameter_m=4.)
    cfg=replace(cfg,heater_max_electric_W=heater*1e6)
    loss=MainHeatLoss(.6*UA,.2*UA,.2*UA) if UA else None
    v=run_closed_cycle(cfg,reverse_discharge=True,valve_loss_K=2.,
        cycles=10,process_duty_W=1e6,cooler_cap_W=cooler,
        main_heat_loss=loss,trace_interval_s=10.,exergy_audit=True)
    for row in v["cycle_records"]:
        for phase in ("charge","discharge"):
            z=row[phase];x=z["exergy_audit"]
            assert x is not None
            assert abs(z["electrical_boundary_residual_J"])<10.
            assert abs(x["exergy_entropy_closure_residual_J"])<10.
            assert all(math.isfinite(y) for y in x["identified_exergy_destruction_J"].values())
            assert abs(z["mass_residual_kg"])<1e-7
            assert x["total_exergy_destruction_J"]>=-max(100.,.001*x["electric_input_exergy_J"])
        d=row["discharge"]
        assert abs(d["water_boundary_heat_J"]-(600e6-d["process_duty_deficit_J"]+d["process_duty_excess_J"]))<10.
    assert abs(v["repeated_sequence_electrical_residual_J"])<50.
    audit=periodic_audit(v["cycle_records"])
    repeats=[]
    for prev,cur in zip(v["cycle_records"][-3:-1],v["cycle_records"][-2:]):
        for phase in ("charge","discharge"):
            for key in ("total_exergy_destruction_J","process_water_exergy_export_J"):
                p=prev[phase]["exergy_audit"][key];q=cur[phase]["exergy_audit"][key]
                repeats.append(abs(p-q)<=max(50.,.005*max(abs(p),abs(q))))
    periodic=bool(audit["approximate_periodic_model_gate_pass"] and all(repeats))
    row=v["cycle_records"][-1];ch,d=row["charge"].copy(),row["discharge"]
    ch["assumed_heater_nameplate_W"]=cfg.heater_max_electric_W
    load=staggered_loads(ch,d,1e6)
    full=bool(periodic and d["simultaneous_target_duration_s"]>=599.999999
        and d["min_delivered_duty_W"]>=998500. and d["max_delivered_duty_W"]<=1001500.
        and d["min_water_outlet_C"]>=149.5 and d["max_water_outlet_C"]<=150.5
        and d["min_hx_water_outlet_at_accepted_nodes_C"]>=150.)
    peak=max(z[k] for z in (ch,d) for k in ("peak_gas_temperature_at_accepted_nodes_K","peak_rock_temperature_at_accepted_nodes_K","peak_wall_temperature_at_accepted_nodes_K"))
    merged={}
    keys=("electric_input_exergy_J","process_water_exergy_export_J",
        "cooler_export_to_assumed_sink_exergy_J","ambient_heat_export_exergy_J",
        "inventory_physical_exergy_change_J","total_exergy_destruction_J",
        "total_entropy_generation_J_K","unresolved_gas_hydraulics_and_numerical_exergy_J")
    for k in keys:merged[k]=sum(z["exergy_audit"][k] for z in (ch,d))
    names=ch["exergy_audit"]["identified_exergy_destruction_J"]
    parts={k:sum(z["exergy_audit"]["identified_exergy_destruction_J"][k] for z in (ch,d)) for k in names}
    def ecl(z):return z["exergy_audit"]["exergy_entropy_closure_residual_J"]
    max_exergy_res=max(abs(ecl(z)) for z in (ch,d))
    # Exergy sinks plus positive sources cannot fully classify flow
    # pressure losses because existing solver has no calibrated compressor EOS.
    summary=dict(case=case,cells=cells,max_step_s=step,heater_nameplate_per_bank_MW=heater,
        heat_leak_UA_W_K=UA,cooler_cap_W=cooler,
        full_matched_service=full,periodic=periodic,thermal_gate=peak<=473.15,
        eligible=bool(full and peak<=473.15),matched_seconds=d["simultaneous_target_duration_s"],
        process_heat_J=d["water_boundary_heat_J"],main_heat_leak_J=ch["main_ambient_heat_J"]+d["main_ambient_heat_J"],
        model_mean_electric_W=load["mean_modeled_electric_W"],
        plant_pump_exergy_input_J=load["modeled_electric_per_slot_J"]-merged["electric_input_exergy_J"],
        exergy=merged,component_exergy_destroyed_J=parts,
        max_exergy_entropy_balance_residual_J=max_exergy_res,
        unresolved_exergy_negative=(merged["unresolved_gas_hydraulics_and_numerical_exergy_J"]<-max(100.,1e-4*merged["electric_input_exergy_J"])),
        target_process_exergy_over_plant_electric=None if not full else merged["process_water_exergy_export_J"]/load["modeled_electric_per_slot_J"],
        physical_equipment_qualified=False,complete_component_exergy_attribution=False)
    print(json.dumps(summary),flush=True)
    return dict(summary=summary,final_cycle_exergy={"charge":ch["exergy_audit"],"discharge":d["exergy_audit"]},
        model_assumptions=v["assumptions"],periodic_audit=audit,geometry=geometry)

def aggregate(path):
    cases={}
    for p in path.rglob("case_*.json"):
        s=json.loads(p.read_text())["summary"];k=s["case"]
        if k in cases or k not in CASES:raise ValueError("duplicate/unknown case")
        if (s["cells"],s["max_step_s"],s["heater_nameplate_per_bank_MW"],s["heat_leak_UA_W_K"],s["cooler_cap_W"])!=CASES[k]:
            raise ValueError("source case mismatch")
        cases[k]=s
    if set(cases)!=set(CASES):raise ValueError("incomplete campaign")
    known={
        "h3_adia_n16":1058471.6585475714,"h5_adia_n16":1058467.0194850015,
        "h3_loss100_n16":1107933.4558105483,
        "h3_loss500_n16":1303752.1292558354,
        "h3_loss1000_n16":1544055.7767529679,
    }
    for k,x in known.items():
        assert abs(cases[k]["model_mean_electric_W"]-x)/x<.005
    reference=cases["h3_loss500_n16"]
    sensitivity={}
    for case in ("h3_loss500_n12","h3_loss500_halfstep"):
        x=cases[case]
        sensitivity[case]=dict(same_eligibility=x["eligible"]==reference["eligible"],
            model_electric_relative_diff=abs(x["model_mean_electric_W"]-reference["model_mean_electric_W"])/reference["model_mean_electric_W"],
            water_exergy_relative_diff=abs(x["exergy"]["process_water_exergy_export_J"]-reference["exergy"]["process_water_exergy_export_J"])/max(1,abs(reference["exergy"]["process_water_exergy_export_J"])),
            destruction_relative_diff=abs(x["exergy"]["total_exergy_destruction_J"]-reference["exergy"]["total_exergy_destruction_J"])/max(1,abs(reference["exergy"]["total_exergy_destruction_J"])))
    x=dict(cases=cases,independent_loss500_sensitivity=sensitivity,
        all_exergy_closures_tested=True,unallocated_entropy_destruction_explicit=True,
        component_allocation_qualified=False,physical_plant_validated=False,
        compressor_map_validated=False,integrated_80C_heat_pump=False,
        Carnot_battery_RTE=None)
    print(json.dumps(x),flush=True)
    return x

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--case",choices=CASES);p.add_argument("--aggregate",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if bool(a.case)==bool(a.aggregate):p.error("use exactly one mode")
    result=run_case(a.case) if a.case else aggregate(a.aggregate)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
