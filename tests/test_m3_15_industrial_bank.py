import math
import pytest
from carnot_battery_lab.physics.industrial_bank import bank_geometry,staggered_loads

def test_geometry_preserves_bed_area_and_inventory():
    g=bank_geometry(1000,20,4.)
    assert g["bed_diameter_each_m"]==pytest.approx(.3*math.sqrt(50))
    assert 20*math.pi*g["bed_diameter_each_m"]**2/4==pytest.approx(g["total_bed_area_m2"])
    assert g["rock_mass_kg"]==pytest.approx(55134.9510705)
    assert g["header_gas_volume_m3"]==pytest.approx(80*math.pi)
    assert bank_geometry(1000,20,3.)["header_equivalent_return_K"]>g["header_equivalent_return_K"]

def test_invalid_vessel_split():
    with pytest.raises(ValueError):bank_geometry(1000,21)

def test_three_bank_schedule_and_energy():
    def trace(n,heater,cooler,delivery):
        return [dict(time_s=t,heater_W=heater,cooler_W=cooler,blower_W=10.,delivered_W=delivery,delivered_C=150.) for t in range(0,n+1,10)]
    ch=dict(duration_s=1200.,phase_trace=trace(1200,1000.,0.,0.),heater_electric_J=1.2e6,
            blower_electric_J=12000.,assumed_heater_nameplate_W=1000.)
    d=dict(duration_s=600.,phase_trace=trace(600,0.,200.,500.),blower_electric_J=6000.,
        cooler_heat_to_assumed_sink_J=120000.,peak_cooler_at_accepted_nodes_W=200.,
        process_demand_flow_kg_s=.003,water_boundary_heat_J=300000.,process_duty_deficit_J=0.)
    s=staggered_loads(ch,d,500.)
    assert len(s["trace"])==61 and s["installed_heater_W"]==3000.
    assert s["sampled_peak_heater_W"]==2000.
    assert all(x["delivered_W"]==500. and x["cooler_W"]==200. for x in s["trace"])
    assert s["modeled_electric_per_slot_J"]==pytest.approx(s["sampled_peak_electric_W"]*600.)
    assert not s["continuous_service_qualified"] and not s["switching_transient_modeled"]

def test_scaled_dynamic_similarity_and_cooler_cap():
    pytest.importorskip("CoolProp");pytest.importorskip("numpy");pytest.importorskip("scipy")
    from dataclasses import replace
    from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
    from carnot_battery_lab.physics.industrial_bank import equivalent_bank
    c=ClosedCycle();c=replace(c,charge_s=120.,discharge_s=60.,train=replace(c.train,bed_cells=2,hx_cells=2))
    a=run_closed_cycle(c,reverse_discharge=True,valve_loss_K=2.,process_duty_W=1000.,cooler_cap_W=100.)
    cfg,_=equivalent_bank(c,modules=4,vessels=2)
    b=run_closed_cycle(cfg,reverse_discharge=True,valve_loss_K=2.,process_duty_W=4000.,cooler_cap_W=400.,trace_interval_s=10.)
    for phase in ("charge","discharge"):
        assert b[phase]["water_boundary_heat_J"]/4==pytest.approx(a[phase]["water_boundary_heat_J"],abs=1.)
        assert b[phase]["final_water_outlet_C"]==pytest.approx(a[phase]["final_water_outlet_C"],abs=.01)
        assert b[phase]["heater_electric_J"]/4==pytest.approx(a[phase]["heater_electric_J"],abs=1.)
        assert b[phase]["peak_cooler_at_accepted_nodes_W"]<=400.
    assert abs(b["discharge"]["electrical_boundary_residual_J"])<.2
