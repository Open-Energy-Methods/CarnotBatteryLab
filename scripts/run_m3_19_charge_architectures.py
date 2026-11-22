"""M3.19 nine matched-service simulations: charge temperature versus process delivery."""
import argparse,json,math
from dataclasses import replace
from pathlib import Path
from carnot_battery_lab.physics.charging_architecture import direct_hp_gate,bounded_hp_preheat

# gas target C, bed/HX cells, max integration step s
CASES={
    "gas190_n16":(190.,16,5.),
    "gas180_n16":(180.,16,5.),
    "gas175_n16":(175.,16,5.),
    "gas165_n16":(165.,16,5.),
    "gas145_n16":(145.,16,5.),
    "gas190_n12":(190.,12,5.),
    "gas175_n12":(175.,12,5.),
    "gas190_halfstep":(190.,16,2.5),
    "gas175_halfstep":(175.,16,2.5),
}
HP_COP_R600A_ASSUMED_80C=2.302054578653484

def run(case):
    from CoolProp.CoolProp import PropsSI
    from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
    from carnot_battery_lab.physics.industrial_bank import equivalent_bank,staggered_loads
    from carnot_battery_lab.physics.thermal_retention import MainHeatLoss
    from carnot_battery_lab.physics.periodic_recovery import periodic_audit

    target,n,step=CASES[case]
    c=ClosedCycle()
    c=replace(c,discharge_s=600.,max_step_s=step,heater_target_K=target+273.15,
        train=replace(c.train,bed_cells=n,hx_cells=n))
    cfg,g=equivalent_bank(c,modules=1000,vessels=20,header_diameter_m=4.)
    cfg=replace(cfg,heater_max_electric_W=3e6)
    v=run_closed_cycle(cfg,reverse_discharge=True,valve_loss_K=2.,cycles=10,
        process_duty_W=1e6,cooler_cap_W=0.,
        main_heat_loss=MainHeatLoss(300.,100.,100.),trace_interval_s=10.)
    for row in v["cycle_records"]:
        for phase in ("charge","discharge"):
            z=row[phase]
            assert abs(z["mass_residual_kg"])<1e-7
            assert max(abs(y) for y in z["component_thermal_residuals_J"].values())<10.
            assert abs(z["electrical_boundary_residual_J"])<10.
            assert z["peak_cooler_at_accepted_nodes_W"]==0.
        d=row["discharge"]
        assert abs(d["water_boundary_heat_J"]-(600e6-d["process_duty_deficit_J"]+d["process_duty_excess_J"]))<10.
        assert abs(d["water_throughput_kg"]-d["process_demand_flow_kg_s"]*600.)<1e-6
    audit=periodic_audit(v["cycle_records"])
    repeat=True
    for prev,cur in zip(v["cycle_records"][-3:-1],v["cycle_records"][-2:]):
        for phase in ("charge","discharge"):
            for key in ("main_rock_ambient_heat_J","main_wall_ambient_heat_J","main_return_ambient_heat_J"):
                p,q=prev[phase][key],cur[phase][key]
                repeat &=abs(p-q)<=max(10.,.005*max(abs(p),abs(q)))
    periodic=bool(audit["approximate_periodic_model_gate_pass"] and repeat)
    row=v["cycle_records"][-1];ch=row["charge"].copy();d=row["discharge"]
    ch["assumed_heater_nameplate_W"]=cfg.heater_max_electric_W
    z=staggered_loads(ch,d,1e6)
    full=bool(periodic and d["simultaneous_target_duration_s"]>=599.999999
        and d["min_delivered_duty_W"]>=998500. and d["max_delivered_duty_W"]<=1001500.
        and d["min_water_outlet_C"]>=149.5 and d["max_water_outlet_C"]<=150.5
        and d["min_hx_water_outlet_at_accepted_nodes_C"]>=150.)
    maxT=max(y[k] for y in (ch,d) for k in (
        "peak_gas_temperature_at_accepted_nodes_K",
        "peak_rock_temperature_at_accepted_nodes_K",
        "peak_wall_temperature_at_accepted_nodes_K"))
    # Air enthalpy for an external prospective inlet preheater only.
    def air_h(T):
        return float(PropsSI("Hmass","T",T,"P",101325.,"HEOS::Air"))
    bound=bounded_hp_preheat(ch,gas_enthalpy=air_h,
        hypothetical_hp_COP=HP_COP_R600A_ASSUMED_80C,
        resistance_efficiency=cfg.heater_efficiency)
    hp_gate=direct_hp_gate(target)
    summary=dict(case=case,target_gas_C=target,cells=n,max_step_s=step,
        approximate_periodic=periodic,full_service=full,thermal_screen=maxT<=473.15,
        eligible=bool(full and maxT<=473.15),
        matched_s=d["simultaneous_target_duration_s"],deficit_J=d["process_duty_deficit_J"],
        final_water_C=d["final_water_outlet_C"],
        raw_HX_margin_K=d["min_hx_water_outlet_at_accepted_nodes_C"]-150.,
        peak_temperature_K=maxT,existing_plant_electric_W=z["mean_modeled_electric_W"],
        heater_charging_electric_J=ch["heater_electric_J"],
        charge_heater_to_gas_J=ch["heater_thermal_to_gas_J"],
        direct_HP_gate=hp_gate,hypothetical_HP150_electric_boost_bound=bound,
        HP150_electric_boost_retrofit_qualified=False,
        80C_source_compressor_map_validated=False,
        heat_pump_storage_dynamic_coupling_demonstrated=False,
        external_HX_pressure_losses_assessed=False,
        Carnot_battery_RTE=None)
    print(json.dumps(dict(case=case,full=full,periodic=periodic,mean_electric_W=z["mean_modeled_electric_W"],
        upper_HP_fraction=bound["upper_bound_HP_fraction"],conditional_saving_J=bound["conditional_upper_bound_electric_saving_J"])),flush=True)
    return dict(summary=summary,periodic_audit=audit,assumptions=v["assumptions"])

def aggregate(root):
    cases={}
    for p in root.rglob("case_*.json"):
        q=json.loads(p.read_text())["summary"];k=q["case"]
        if k not in CASES or k in cases:raise ValueError("duplicate/unknown case")
        if (q["target_gas_C"],q["cells"],q["max_step_s"])!=CASES[k]:raise ValueError("case mismatch")
        cases[k]=q
    if set(cases)!=set(CASES):raise ValueError("incomplete comparison")
    # Existing validated M3.16b reference with 500 W/K loss and 3 MW heater.
    ref=cases["gas190_n16"]
    if not ref["full_service"] or abs(ref["existing_plant_electric_W"]-1303752.1292558354)/1303752.1292558354>.005:
        raise ValueError("the existing fixed-service reference changed")
    comparisons={}
    for target in (190,175):
        key=f"gas{target}_n16"
        a=cases[key]
        other=("gas190_n12","gas190_halfstep") if target==190 else ("gas175_n12","gas175_halfstep")
        rows={}
        for q in other:
            b=cases[q]
            rows[q]=dict(same_full_service_gate=a["eligible"]==b["eligible"],
                mean_electric_relative_diff=abs(a["existing_plant_electric_W"]-b["existing_plant_electric_W"])/a["existing_plant_electric_W"],
                raw_HX_margin_difference_K=abs(a["raw_HX_margin_K"]-b["raw_HX_margin_K"]))
        comparisons[str(target)]=rows
    out=dict(cases=cases,mesh_step_checks=comparisons,
        thermally_compatible_HP150_charge_candidates=[k for k,v in cases.items() if v["eligible"] and v["direct_HP_gate"]["water_temperature_suffices"]],
        redesigned_charge_targets_matching_same_process_service=[k for k,v in cases.items() if v["eligible"]],
        booster_results_are_upper_bounds_only=True,
        source80_heat_pump_compressor_map_not_validated=True,
        integrated_Carnot_battery_RTE=None,measured_HP_TES_performance=None)
    print(json.dumps(out),flush=True)
    return out

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--case",choices=CASES);p.add_argument("--aggregate",type=Path)
    p.add_argument("--output",required=True,type=Path);a=p.parse_args()
    if bool(a.case)==bool(a.aggregate):p.error("choose exactly one mode")
    x=run(a.case) if a.case else aggregate(a.aggregate)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(x,indent=2,allow_nan=False)+"\n")
