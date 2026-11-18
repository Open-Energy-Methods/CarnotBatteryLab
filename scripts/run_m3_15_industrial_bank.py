"""Fixed 1 MW duty, independent industrial surrogate case jobs."""
import argparse,json
from dataclasses import replace
from pathlib import Path
from carnot_battery_lab.physics.industrial_bank import equivalent_bank,staggered_loads

CASES={
    "ideal_similarity":(16,None,None),
    "header_3m":(16,3.,None),
    "header_4m":(16,4.,None),
    "header_4m_cap3MW":(16,4.,3e6),
    "header_4m_cap1MW":(16,4.,1e6),
    "header_4m_cap3MW_coarse":(12,4.,3e6),
}

def run_case(name):
    from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
    from carnot_battery_lab.physics.periodic_recovery import periodic_audit
    n,D,cap=CASES[name]
    b=ClosedCycle()
    b=replace(b,discharge_s=600.,train=replace(b.train,bed_cells=n,hx_cells=n))
    c,g=equivalent_bank(b,modules=1000,vessels=20,header_diameter_m=D)
    result=run_closed_cycle(c,reverse_discharge=True,valve_loss_K=2.,cycles=10,
        process_duty_W=1e6,cooler_cap_W=cap,trace_interval_s=10.)
    for row in result["cycle_records"]:
        for phase in ("charge","discharge"):
            z=row[phase]
            assert abs(z["mass_residual_kg"])<1e-7
            assert max(abs(x) for x in z["component_thermal_residuals_J"].values())<10.
            assert abs(z["electrical_boundary_residual_J"])<10.
            if cap is not None:assert z["peak_cooler_at_accepted_nodes_W"]<=cap+1e-8
        d=row["discharge"]
        assert abs(d["water_throughput_kg"]-d["process_demand_flow_kg_s"]*600.)<1e-6
        assert abs(d["water_boundary_heat_J"]-(600e6-d["process_duty_deficit_J"]+d["process_duty_excess_J"]))<10.
    assert abs(result["repeated_sequence_mass_residual_kg"])<1e-7
    assert abs(result["repeated_sequence_electrical_residual_J"])<50.
    audit=periodic_audit(result["cycle_records"])
    row=result["cycle_records"][-1]
    ch,d=row["charge"].copy(),row["discharge"]
    ch["assumed_heater_nameplate_W"]=c.heater_max_electric_W
    s=staggered_loads(ch,d,1e6)
    periodic=audit["approximate_periodic_model_gate_pass"]
    full=bool(periodic and d["simultaneous_target_duration_s"]>=599.999999
        and d["min_delivered_duty_W"]>=998500. and d["max_delivered_duty_W"]<=1001500.
        and d["min_water_outlet_C"]>=149.5 and d["max_water_outlet_C"]<=150.5)
    summary=dict(case=name,cells=n,header_D_m=D,cooler_cap_W=cap,periodic=periodic,
        bank_full_modeled_service=full,matched_s=d["simultaneous_target_duration_s"],
        deficit_J=d["process_duty_deficit_J"],raw_margin_K=d["min_hx_water_outlet_at_accepted_nodes_C"]-150.,
        final_C=d["final_water_outlet_C"],bank_electric_J=ch["heater_electric_J"]+ch["blower_electric_J"]+d["blower_electric_J"],
        bank_cooler_J=d["cooler_heat_to_assumed_sink_J"],
        bank_peak_cooler_W=d["peak_cooler_at_accepted_nodes_W"],
        bank_peak_gas_flow_kg_s=max(x["peak_blower_flow_at_accepted_nodes_kg_s"] for x in (ch,d)),
        plant_mean_electric_W=s["mean_modeled_electric_W"],plant_sampled_peak_electric_W=s["sampled_peak_electric_W"],
        plant_sampled_peak_heater_W=s["sampled_peak_heater_W"],plant_sampled_peak_coolant_pump_W=s["sampled_peak_coolant_pump_W"],
        plant_installed_heater_W=s["installed_heater_W"],plant_rock_mass_kg=3*g["rock_mass_kg"],
        continuous_service_qualified=False,industrial_service_qualified=False)
    print(json.dumps(summary),flush=True)
    return dict(summary=summary,geometry=g,periodic_audit=audit,schedule=s,result=result)

def aggregate(root):
    cases={}
    for p in root.rglob("case_*.json"):
        v=json.loads(p.read_text());s=v["summary"];name=s["case"]
        if name not in CASES or name in cases:raise ValueError("duplicate or unknown case")
        if (s["cells"],s["header_D_m"],s["cooler_cap_W"])!=CASES[name]:raise ValueError("case mismatch")
        cases[name]=s
    if set(cases)!=set(CASES):raise ValueError("incomplete campaign")
    # Analytic similarity control versus M3.14b exact verified 16-cell 1 kW
    # prototype reference; allow numerical noise, not hardware transfer.
    a=cases["ideal_similarity"]
    similarity=dict(reference_module_electric_J=1884194.7835619815,
        electric_relative_difference=abs(a["bank_electric_J"]/1000.-1884194.7835619815)/1884194.7835619815,
        raw_margin_difference_K=abs(a["raw_margin_K"]-3.011664491347915))
    assert similarity["electric_relative_difference"]<.01 and similarity["raw_margin_difference_K"]<.1
    assert a["bank_full_modeled_service"]
    fine,coarse=cases["header_4m_cap3MW"],cases["header_4m_cap3MW_coarse"]
    sensitivity=dict(same_full_gate=fine["bank_full_modeled_service"]==coarse["bank_full_modeled_service"],
        raw_margin_difference_K=abs(fine["raw_margin_K"]-coarse["raw_margin_K"]),
        electric_relative_difference=abs(fine["bank_electric_J"]-coarse["bank_electric_J"])/fine["bank_electric_J"])
    x=dict(cases=cases,similarity_control=similarity,cap3MW_spatial_sensitivity=sensitivity,
        full_discrete_cases=[k for k,v in cases.items() if v["bank_full_modeled_service"]],
        hardware_qualified=False,industrial_service_qualified=False,continuous_service_qualified=False,
        Carnot_battery_RTE=None)
    print(json.dumps(x),flush=True)
    return x

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--case",choices=CASES);p.add_argument("--aggregate",type=Path)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    if bool(a.case)==bool(a.aggregate):p.error("select exactly one mode")
    x=run_case(a.case) if a.case else aggregate(a.aggregate)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(x,indent=2,allow_nan=False)+"\n")
