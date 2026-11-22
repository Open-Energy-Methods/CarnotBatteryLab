"""Dynamic, finite-capacity HP charging with explicit 80C source and pumps."""
import argparse,json,math
from dataclasses import replace
from pathlib import Path
from carnot_battery_lab.physics.dynamic_hp_charger import HPChargeInterface
from carnot_battery_lab.physics.thermal_retention import MainHeatLoss
from carnot_battery_lab.physics.industrial_bank import equivalent_bank,staggered_loads

# Capacity W, conductance W/K, source/hot-water flow kg/s, grid, max step.
CASES={
    "electric_only":(0.,0.,0.,0.,16,5.),
    "hp500_ua25k":(5e5,25000.,20.,10.,16,5.),
    "hp1000_ua25k":(1e6,25000.,20.,10.,16,5.),
    "hp1000_ua100k":(1e6,100000.,20.,10.,16,5.),
    "hp1000_ua100k_n12":(1e6,100000.,20.,10.,12,5.),
    "hp1000_ua100k_halfstep":(1e6,100000.,20.,10.,16,2.5),
    "hp1000_ua100k_limitedwater":(1e6,100000.,2.,1.,16,5.),
}

def run(case):
    from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
    from carnot_battery_lab.physics.periodic_recovery import periodic_audit
    cap,UA,source_flow,water_flow,n,step=CASES[case]
    base=ClosedCycle()
    base=replace(base,discharge_s=600.,max_step_s=step,
        train=replace(base.train,bed_cells=n,hx_cells=n))
    c,g=equivalent_bank(base,modules=1000,vessels=20,header_diameter_m=4.)
    c=replace(c,heater_max_electric_W=3e6)
    hp=(HPChargeInterface(hp_thermal_nameplate_W=cap,
            gas_UA_W_K=UA,source_water_max_flow_kg_s=source_flow,
            hot_water_max_flow_kg_s=water_flow)
        if cap else None)
    v=run_closed_cycle(c,reverse_discharge=True,valve_loss_K=2.,
        cycles=10,process_duty_W=1e6,cooler_cap_W=0.,
        main_heat_loss=MainHeatLoss(300.,100.,100.),
        hp_charger=hp,trace_interval_s=10.)
    for row in v["cycle_records"]:
        for stage in ("charge","discharge"):
            z=row[stage]
            assert abs(z["electrical_boundary_residual_J"])<10.
            assert abs(z["mass_residual_kg"])<1e-7
            assert max(abs(y) for y in z["component_thermal_residuals_J"].values())<10.
            assert abs(z["HP_heat_to_gas_J"]-z["HP_compressor_electric_J"]-z["HP_source_heat_J"])<10.
            if cap:
                assert z["HP_heat_to_gas_J"]<=cap*z["duration_s"]+10.
                assert z["HP_source_water_mass_kg"]<=source_flow*z["duration_s"]+1e-5
                assert z["HP_hot_water_mass_kg"]<=water_flow*z["duration_s"]+1e-5
            if stage=="discharge":
                assert z["HP_heat_to_gas_J"]==z["HP_compressor_electric_J"]==0.
        d=row["discharge"]
        assert abs(d["water_boundary_heat_J"]-(600e6-d["process_duty_deficit_J"]+d["process_duty_excess_J"]))<10.
    assert abs(v["repeated_sequence_electrical_residual_J"])<50.
    audit=periodic_audit(v["cycle_records"])
    HP_periodic=True
    for a,b in zip(v["cycle_records"][-3:-1],v["cycle_records"][-2:]):
        for phase in ("charge","discharge"):
            for key in ("HP_heat_to_gas_J","HP_compressor_electric_J",
                        "HP_source_heat_J","HP_circulation_pump_electric_J",
                        "HP_source_water_mass_kg","HP_hot_water_mass_kg"):
                x,y=a[phase][key],b[phase][key]
                HP_periodic &=abs(x-y)<=max(10.,.005*max(abs(x),abs(y)))
    p=bool(audit["approximate_periodic_model_gate_pass"] and HP_periodic)
    row=v["cycle_records"][-1];ch=row["charge"].copy();d=row["discharge"]
    ch["assumed_heater_nameplate_W"]=c.heater_max_electric_W
    load=staggered_loads(ch,d,1e6)
    HP_electrical=ch["HP_compressor_electric_J"]+ch["HP_circulation_pump_electric_J"]
    all_electric=load["modeled_electric_per_slot_J"]+HP_electrical
    full=bool(p and d["simultaneous_target_duration_s"]>=599.999999
        and d["min_delivered_duty_W"]>=998500. and d["max_delivered_duty_W"]<=1001500.
        and d["min_water_outlet_C"]>=149.5 and d["max_water_outlet_C"]<=150.5
        and d["min_hx_water_outlet_at_accepted_nodes_C"]>=150.)
    tmax=max(z[k] for z in (ch,d) for k in (
        "peak_gas_temperature_at_accepted_nodes_K",
        "peak_rock_temperature_at_accepted_nodes_K",
        "peak_wall_temperature_at_accepted_nodes_K"))
    s=dict(case=case,HP_rated_thermal_W=cap,HP_UA_W_K=UA,HP_max_source_kg_s=source_flow,
        HP_max_hot_water_kg_s=water_flow,cells=n,max_step_s=step,
        periodic=p,HP_ledger_periodic=HP_periodic,full_service=full,
        thermal_limit_pass=tmax<=473.15,eligible=bool(full and tmax<=473.15),
        service_duration_s=d["simultaneous_target_duration_s"],deficit_J=d["process_duty_deficit_J"],
        HX_raw_margin_K=d["min_hx_water_outlet_at_accepted_nodes_C"]-150.,
        modeled_plant_electric_W=all_electric/600.,
        energy_per_slot_electric_J=all_electric,
        charge_booster_electric_J=ch["heater_electric_J"],
        charge_HP_compressor_electric_J=ch["HP_compressor_electric_J"],
        charge_HP_water_pump_electric_J=ch["HP_circulation_pump_electric_J"],
        charge_HP_heat_to_gas_J=ch["HP_heat_to_gas_J"],
        charge_external_source_heat_J=ch["HP_source_heat_J"],
        charge_source_water_mass_kg=ch["HP_source_water_mass_kg"],
        charge_hot_water_mass_kg=ch["HP_hot_water_mass_kg"],
        charging_thermal_input_closure_J=ch["HP_heat_to_gas_J"]-ch["HP_source_heat_J"]-ch["HP_compressor_electric_J"],
        HP_COP_assumed=2.302054578653484 if hp else None,
        HP_compressor_hardware_qualified=False,HP_source_available_in_site=False,
        HP_capacity_and_speed_measured=False,
        TES_process_service_measured=False,HP_TES_no_HX_inventory_assumption=True,
        complete_Carnot_battery_RTE=None)
    print(json.dumps({k:s[k] for k in ("case","full_service","periodic","modeled_plant_electric_W",
        "charge_HP_heat_to_gas_J","charge_HP_compressor_electric_J")}),flush=True)
    return dict(summary=s,periodic_audit=audit,assumptions=v["assumptions"],geometry=g)

def aggregate(root):
    cases={}
    for p in root.rglob("case_*.json"):
        z=json.loads(p.read_text())["summary"];k=z["case"]
        if k not in CASES or k in cases:raise ValueError("duplicate/unknown case")
        assert (z["HP_rated_thermal_W"],z["HP_UA_W_K"],z["HP_max_source_kg_s"],
            z["HP_max_hot_water_kg_s"],z["cells"],z["max_step_s"])==CASES[k]
        cases[k]=z
    if set(cases)!=set(CASES):raise ValueError("missing matrix cases")
    ref=cases["electric_only"]
    if not ref["full_service"] or abs(ref["modeled_plant_electric_W"]-1303752.1292558354)/1303752.1292558354>.005:
        raise ValueError("reference TES energy performance drift")
    base=cases["hp1000_ua100k"]
    sensitivity={}
    for k in ("hp1000_ua100k_n12","hp1000_ua100k_halfstep"):
        v=cases[k]
        sensitivity[k]=dict(both_eligible=base["eligible"] and v["eligible"],
            electric_relative_difference=abs(v["modeled_plant_electric_W"]-base["modeled_plant_electric_W"])/base["modeled_plant_electric_W"],
            HP_thermal_relative_difference=abs(v["charge_HP_heat_to_gas_J"]-base["charge_HP_heat_to_gas_J"])/max(1.,base["charge_HP_heat_to_gas_J"]),
            service_same=base["full_service"]==v["full_service"])
    screened=[v for v in cases.values() if v["eligible"] and v["cells"]==16 and v["max_step_s"]==5.]
    best=min(screened,key=lambda x:x["modeled_plant_electric_W"])["case"] if screened else None
    result=dict(cases=cases,independent_HX_TES_numerical_sensitivity=sensitivity,
        lowest_model_electric_case=best,
        note="All model results contingent on constant unqualified HP COP, ideal hot-water supply and instantaneous control",
        heat_source_and_water_pumps_accounted_but_source_availability_unqualified=True,
        compressor_map_qualified=False,heat_pump_refrigerant_transients_modeled=False,
        industrial_HAZOP_qualified=False,complete_Carnot_battery_RTE=None)
    print(json.dumps(result),flush=True);return result

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--case",choices=CASES);p.add_argument("--aggregate",type=Path)
    p.add_argument("--output",required=True,type=Path);a=p.parse_args()
    if bool(a.case)==bool(a.aggregate):p.error("choose one mode")
    x=run(a.case) if a.case else aggregate(a.aggregate)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(x,indent=2,allow_nan=False)+"\n")
