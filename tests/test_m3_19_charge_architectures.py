import pytest
from carnot_battery_lab.physics.charging_architecture import direct_hp_gate,bounded_hp_preheat

def trace(temp=400.,q=1000.,m=1.):
    a=dict(duration_s=100.,heater_thermal_to_gas_J=100000.,
        heater_electric_J=100000./.95)
    a["phase_trace"]=[dict(time_s=t,heater_to_gas_W=q,
        gas_flow_kg_s=m,return_gas_K=temp) for t in (0.,50.,100.)]
    return a

def test_charging_temperature_and_rating_gates():
    a=direct_hp_gate(190.)
    assert a["required_hot_water_outlet_C"]==195.
    assert a["required_compressor_discharge_C"]==200.
    assert not a["water_temperature_suffices"] and not a["directly_compatible"]
    assert direct_hp_gate(145.)["directly_compatible"]
    assert not direct_hp_gate(165.)["directly_compatible"]
    assert not direct_hp_gate(145.,hp_compressor_discharge_limit_C=154.)["directly_compatible"]

def test_absolute_upper_bound_and_first_law_split():
    a=bounded_hp_preheat(trace(),gas_enthalpy=lambda t:1000.*t,
        hypothetical_hp_COP=2.3)
    assert a["upper_bound_HP_contribution_J"]==pytest.approx(100000.)
    assert a["lower_bound_electric_booster_J"]==0.
    assert a["hypothetical_source_heat_J"]+a["hypothetical_HP_compressor_electric_J"]==pytest.approx(100000.)
    assert a["conditional_upper_bound_electric_saving_J"]>0.
    assert not a["physically_qualified_saving"]

def test_return_gas_too_hot_for_hp_preheater():
    a=bounded_hp_preheat(trace(450.),gas_enthalpy=lambda t:1000.*t)
    assert a["upper_bound_HP_fraction"]==0.
    assert a["conditional_upper_bound_electric_saving_J"]==pytest.approx(0.)
    assert a["lower_bound_electric_booster_J"]==pytest.approx(trace()["heater_electric_J"])

def test_partial_mass_flow_limits_hp_contribution():
    a=bounded_hp_preheat(trace(temp=417.,m=.1),gas_enthalpy=lambda t:1000.*t)
    assert 0<a["upper_bound_HP_fraction"]<1.
    assert a["lower_bound_electric_booster_J"]>0.

@pytest.mark.parametrize("wrong",["bad_interval","bad_energy","bad_COP","negative_flow"])
def test_fails_closed_on_trace_disagreement(wrong):
    a=trace()
    kwargs=dict(gas_enthalpy=lambda t:1000.*t)
    if wrong=="bad_interval":a["phase_trace"][-1]["time_s"]=99.
    if wrong=="bad_energy":a["heater_thermal_to_gas_J"]=200000.
    if wrong=="bad_COP":kwargs["hypothetical_hp_COP"]=1.
    if wrong=="negative_flow":a["phase_trace"][0]["gas_flow_kg_s"]=-1.
    with pytest.raises(ValueError):bounded_hp_preheat(a,**kwargs)

def test_real_air_trace_is_model_consistent():
    pytest.importorskip("numpy");pytest.importorskip("scipy");pytest.importorskip("CoolProp")
    from dataclasses import replace
    from CoolProp.CoolProp import PropsSI
    from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
    c=ClosedCycle();c=replace(c,charge_s=120.,discharge_s=60.,
        train=replace(c.train,bed_cells=2,hx_cells=2))
    d=run_closed_cycle(c,process_duty_W=1000.,cooler_cap_W=0.,
        trace_interval_s=10.,reverse_discharge=True)
    charge=d["charge"]
    assert all("return_gas_K" in z and "heater_to_gas_W" in z for z in charge["phase_trace"])
    a=bounded_hp_preheat(charge,
        gas_enthalpy=lambda t:PropsSI("Hmass","T",t,"P",101325.,"HEOS::Air"))
    assert 0<=a["upper_bound_HP_fraction"]<=1.
    assert a["lower_bound_electric_booster_J"]>=0.
