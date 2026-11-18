"""Regenerate small closed-loop real-air thermal sequence, not industrial."""
import argparse,json
from dataclasses import replace
from pathlib import Path
from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle

def study():
    base=ClosedCycle()
    cases={
        "baseline":base,
        "coarse_grid":replace(base,train=replace(base.train,bed_cells=2,hx_cells=2)),
        "refined_grid":replace(base,train=replace(base.train,bed_cells=4,hx_cells=4)),
        "smaller_blower_head":replace(base,blower_shutoff_head_Pa=300.),
        "lower_cooler_UA":replace(base,cooler_UA_W_K=30.),
        "shorter_charge":replace(base,charge_s=600.),
        "half_max_step":replace(base,max_step_s=2.5),
    }
    out={}
    for name,c in cases.items():
        r=run_closed_cycle(c)
        ch,di=r["charge"],r["discharge"]
        summary={"case":name,
            "charge_heater_electric_kWh":ch["heater_electric_J"]/3.6e6,
            "charge_solid_heat_kWh":ch["solid_energy_change_J"]/3.6e6,
            "discharge_water_heat_kWh_NOT_qualified":di["water_boundary_heat_J"]/3.6e6,
            "discharge_cooler_heat_kWh":di["cooler_heat_to_assumed_sink_J"]/3.6e6,
            "total_blower_electric_Wh":(ch["blower_electric_J"]+di["blower_electric_J"])/3600.,
            "final_discharge_water_C":di["final_water_outlet_C"],
            "peak_gas_pressure_accepted_nodes_Pa":max(ch["peak_gas_pressure_at_accepted_nodes_Pa"],di["peak_gas_pressure_at_accepted_nodes_Pa"]),
            "min_discharge_water_C":di["min_water_outlet_C"],
            "max_discharge_water_C":di["max_water_outlet_C"],
            "remaining_solid_inventory_kWh":r["remaining_solid_inventory_above_initial_J"]/3.6e6,
            "all_discharge_accepted_water_nodes_ge_150C":r["all_discharge_accepted_water_nodes_ge_150C"],
            "max_abs_component_thermal_residual_J":max(abs(v) for p in (ch,di) for v in p["component_thermal_residuals_J"].values()),
            "whole_mass_residual_kg":r["whole_cycle_gas_mass_residual_kg"],
            "whole_electric_boundary_residual_J":r["whole_sequence_electrical_boundary_residual_J"]}
        out[name]={"summary":summary,"result":r}
        print("M3_10_CASE",json.dumps(summary),flush=True)
    return {"research_stage":"M3_10_CLOSED_REAL_AIR_THERMAL_SEQUENCE",
            "results":out,"original_industrial_service_qualified":False,
            "external_pump_and_cooling_electricity_excluded":True,
            "Carnot_battery_RTE":None}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("results/m3_10_closed_real_air_cycle.json"))
    a=p.parse_args();r=study()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
