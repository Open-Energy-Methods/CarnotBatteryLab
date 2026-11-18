"""M3.15 hypothetical large-vessel bank and auxiliary-load screen.

A bank is a uniform-flow area-equivalent model, not a 3D vessel or a
qualified manifold network. No cross-bank gas sharing is assumed.
"""
import math
from dataclasses import replace

def bank_geometry(modules=1000,vessels=20,header_diameter_m=None,header_length_each_m=10.,header_friction=.02,header_minor_K=4.):
    if any(isinstance(x,bool) or not isinstance(x,int) or x<=0 for x in (modules,vessels)) or modules%vessels:
        raise ValueError("positive integer vessels must divide module equivalents")
    if not all(math.isfinite(x) and x>0 for x in (header_length_each_m,header_friction,header_minor_K)):
        raise ValueError("invalid header assumptions")
    area=.012*modules
    bed_area=modules*math.pi*.3**2/4
    h_area=h_vol=extra_K=0.
    if header_diameter_m is not None:
        if not math.isfinite(header_diameter_m) or header_diameter_m<=0:
            raise ValueError("invalid header diameter")
        h_area=math.pi*header_diameter_m**2/4
        h_vol=2*header_length_each_m*h_area
        extra_K=(header_friction*2*header_length_each_m/header_diameter_m+header_minor_K)*(area/h_area)**2
    return dict(module_equivalents=modules,vessels_per_bank=vessels,
        bed_length_m=.5,bed_diameter_each_m=.3*math.sqrt(modules/vessels),
        equivalent_bed_diameter_m=.3*math.sqrt(modules),total_bed_area_m2=bed_area,
        bed_bulk_m3=bed_area*.5,rock_mass_kg=bed_area*.5*.6*2600.,
        header_diameter_m=header_diameter_m,header_area_m2=h_area,header_gas_volume_m3=h_vol,
        header_equivalent_return_K=extra_K,header_length_each_m=header_length_each_m,
        header_friction_assumed=header_friction,header_total_minor_K=header_minor_K,
        hx_gas_area_m2=area,hx_UA_W_K=120.*modules,heater_nameplate_W=5000.*modules)

def equivalent_bank(base,modules=1000,vessels=20,header_diameter_m=None):
    """Scale extensive states and areas; preserve local channel Dh and bed depth.

    Header resistance uses a full-flow two-header equivalent and lumped
    gas volume in the return state. Equal vessel flow is imposed.
    """
    g=bank_geometry(modules,vessels,header_diameter_m)
    a=base.train
    train=replace(a,bed_diameter_m=a.bed_diameter_m*math.sqrt(modules),
        hx_gas_volume_m3=a.hx_gas_volume_m3*modules,
        hx_gas_flow_area_m2=a.hx_gas_flow_area_m2*modules,
        hx_overall_UA_W_K=a.hx_overall_UA_W_K*modules,
        hx_water_mass_kg=a.hx_water_mass_kg*modules,
        hx_wall_C_J_K=a.hx_wall_C_J_K*modules,
        water_flow_kg_s=a.water_flow_kg_s*modules)
    cfg=replace(base,train=train,return_gas_volume_m3=base.return_gas_volume_m3*modules+g["header_gas_volume_m3"],
        return_area_m2=base.return_area_m2*modules,
        return_loss_K=base.return_loss_K+g["header_equivalent_return_K"],
        blower_assumed_zero_head_flow_kg_s=base.blower_assumed_zero_head_flow_kg_s*modules,
        heater_max_electric_W=base.heater_max_electric_W*modules,
        heater_feedback_W_K=base.heater_feedback_W_K*modules,
        cooler_UA_W_K=base.cooler_UA_W_K*modules)
    return cfg,g

def staggered_loads(charge,discharge,duty_W,*,water_dp_Pa=1e5,coolant_dp_Pa=1e5,eff=.65,
                    water_rho=930.,coolant_rho=970.,coolant_cp=4180.,coolant_rise_K=10.):
    """3 banks offset by 600 s; compare discrete samples on both sides of switches.

    Energy totals are from integrated stage ledgers, not sampled quadrature.
    Requires 1200/600 s and aligned 10 s traces. Not a transient switch model.
    """
    vals=(duty_W,water_dp_Pa,coolant_dp_Pa,eff,water_rho,coolant_rho,coolant_cp,coolant_rise_K)
    if not all(math.isfinite(x) and x>0 for x in vals) or eff>1:
        raise ValueError("invalid utility parameters")
    if charge["duration_s"]!=1200. or discharge["duration_s"]!=600.:
        raise ValueError("schedule requires two charge slots and one discharge slot")
    ct,dt=charge["phase_trace"],discharge["phase_trace"]
    if [x["time_s"] for x in ct]!=list(range(0,1201,10)) or [x["time_s"] for x in dt]!=list(range(0,601,10)):
        raise ValueError("schedule requires aligned phase traces")
    water_flow=discharge["process_demand_flow_kg_s"]
    wp=water_flow/water_rho*water_dp_Pa/eff
    cool_factor=coolant_dp_Pa/(eff*coolant_rho*coolant_cp*coolant_rise_K)
    # Every 600 s interval contains one bank at each local phase.
    # Endpoints describe one-sided switch states, not finite switching.
    trace=[]
    for i in range(61):
        a,b,c=ct[i],ct[i+60],dt[i]
        heater=a["heater_W"]+b["heater_W"]+c["heater_W"]
        blower=a["blower_W"]+b["blower_W"]+c["blower_W"]
        cooler=a["cooler_W"]+b["cooler_W"]+c["cooler_W"]
        cp=cooler*cool_factor
        trace.append(dict(time_s=i*10,active_charging_banks=2,active_discharge_banks=1,
            heater_W=heater,blower_W=blower,cooler_W=cooler,process_pump_W=wp,
            coolant_pump_W=cp,modeled_electric_W=heater+blower+wp+cp,
            delivered_W=c["delivered_W"],delivered_C=c["delivered_C"]))
    # One 600 s slot consumes the energy of one complete bank cycle.
    E=charge["heater_electric_J"]+charge["blower_electric_J"]+discharge["blower_electric_J"]
    Ec=discharge["cooler_heat_to_assumed_sink_J"]*cool_factor
    total=E+wp*600.+Ec
    return dict(banks=3,charge_slots=2,discharge_slots=1,slot_s=600.,
        installed_heater_W=3*charge["assumed_heater_nameplate_W"],
        requested_heat_J=duty_W*600.,delivered_heat_J=discharge["water_boundary_heat_J"],
        unmet_heat_J=discharge["process_duty_deficit_J"],modeled_electric_per_slot_J=total,
        process_pump_W=wp,coolant_pump_energy_per_slot_J=Ec,
        mean_modeled_electric_W=total/600.,
        sampled_peak_electric_W=max(x["modeled_electric_W"] for x in trace),
        sampled_peak_heater_W=max(x["heater_W"] for x in trace),
        sampled_peak_cooler_W=max(x["cooler_W"] for x in trace),
        sampled_peak_coolant_pump_W=max(x["coolant_pump_W"] for x in trace),
        bank_accepted_node_peak_cooler_W=discharge["peak_cooler_at_accepted_nodes_W"],
        nominal_continuous_schedule=True,continuous_service_qualified=False,
        switching_transient_modeled=False,cross_bank_interaction_modeled=False,
        external_heat_rejection_equipment_electricity_included=False,trace=trace)
