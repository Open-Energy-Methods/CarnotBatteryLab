"""M3.20 dynamic HP charge, no hardware/experimental claims."""
import pytest
from carnot_battery_lab.physics.dynamic_hp_charger import HPChargeInterface,lossless_heat_balance

def fake_water_and_air(out,i1,T,i2,P,fluid):
    assert out=="Hmass" and i1=="T" and i2=="P"
    return (4200. if "Water" in fluid else 1000.)*T

def args(T=393.15,q=200000.,m=2.):
    return dict(charge=True,return_gas_T_K=T,return_gas_P_Pa=101325.,
        return_gas_h_J_kg=1000.*T,gas_mass_flow_kg_s=m,
        requested_gas_heating_W=q,resistance_heater_efficiency=.95,
        props=fake_water_and_air)

def test_energy_and_mass_capacity_and_electric_boost():
    hp=HPChargeInterface()
    r=hp.split(**args())
    assert r["heat_pump_to_gas_W"]==pytest.approx(50000.)
    assert r["booster_heat_to_gas_W"]==pytest.approx(150000.)
    assert r["booster_electric_W"]==pytest.approx(150000./.95)
    assert abs(lossless_heat_balance(r))<1e-7
    assert r["hot_water_flow_kg_s"]<=hp.hot_water_max_flow_kg_s
    assert r["source_water_flow_kg_s"]<=hp.source_water_max_flow_kg_s
    assert r["circulation_pump_electric_W"]>0.
    assert not r["COP_not_compressor_map_validated"] is False

def test_hot_gas_and_discharge_have_zero_HP():
    hp=HPChargeInterface()
    r=hp.split(**args(T=430.15))
    assert r["heat_pump_to_gas_W"]==0.
    assert r["booster_electric_W"]==pytest.approx(200000./.95)
    charge_args=args();charge_args["charge"]=False
    r=hp.split(**charge_args)
    assert r["heat_pump_to_gas_W"]==r["booster_electric_W"]==0.

def test_water_source_and_nameplate_limited():
    hp=HPChargeInterface(hot_water_max_flow_kg_s=.05,source_water_max_flow_kg_s=.08,
                         hp_thermal_nameplate_W=10000.)
    r=hp.split(**args(m=10.))
    assert r["heat_pump_to_gas_W"]<=10000.
    assert r["hot_water_flow_kg_s"]<=.05+1e-10
    assert r["source_water_flow_kg_s"]<=.08+1e-10
    assert abs(lossless_heat_balance(r))<1e-8

@pytest.mark.parametrize("config",[{"hot_water_supply_C":180.},{"COP_electric_assumed":1.},
    {"source_inlet_C":50.},{"gas_UA_W_K":0.},{"gas_minor_loss_K":-1.}])
def test_reject_outside_assumed_equipment_limits(config):
    with pytest.raises(ValueError):HPChargeInterface(**config)

def test_negative_gas_flow_rejected():
    with pytest.raises(ValueError):HPChargeInterface().split(**args(m=-.1))

def test_m3_20_dynamic_stage_conserves_all_energy_and_reverts_to_baseline():
    pytest.importorskip("CoolProp")
    pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    from dataclasses import replace
    from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
    c=ClosedCycle()
    c=replace(c,charge_s=120.,discharge_s=60.,
        train=replace(c.train,bed_cells=2,hx_cells=2))
    base=run_closed_cycle(c,reverse_discharge=True,process_duty_W=1000.,
        cooler_cap_W=0.,cycles=2)
    hp=HPChargeInterface(gas_minor_loss_K=0.,
        gas_UA_W_K=5000.,hp_thermal_nameplate_W=500.)
    out=run_closed_cycle(c,reverse_discharge=True,process_duty_W=1000.,
        cooler_cap_W=0.,cycles=2,hp_charger=hp,trace_interval_s=10.)
    q=out["charge"]
    assert q["HP_heat_to_gas_J"]>0.
    assert q["HP_compressor_electric_J"]>0.
    assert q["HP_source_heat_J"]>0.
    assert q["HP_circulation_pump_electric_J"]>0.
    assert q["heater_electric_J"]<base["charge"]["heater_electric_J"]
    assert (q["HP_compressor_electric_J"]+q["HP_source_heat_J"])==pytest.approx(
        q["HP_heat_to_gas_J"],abs=.01)
    assert q["heater_thermal_to_gas_J"]+q["HP_heat_to_gas_J"]==pytest.approx(
        base["charge"]["heater_thermal_to_gas_J"],abs=5.)
    for row in out["cycle_records"]:
        for stage in ("charge","discharge"):
            a=row[stage]
            assert abs(a["electrical_boundary_residual_J"])<.2
            assert max(abs(v) for v in a["component_thermal_residuals_J"].values())<.2
    assert out["discharge"]["HP_heat_to_gas_J"]==0.
    assert out["total_electric_including_HP_and_aux_pumps_J"]>0.
    assert out["hardware_qualified"] is False
