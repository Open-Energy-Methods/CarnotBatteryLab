import pytest
pytest.importorskip("CoolProp")
pytest.importorskip("numpy")
pytest.importorskip("scipy")
from dataclasses import replace
from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle,process_water_split

@pytest.mark.parametrize("h",[-10.,0.,20.,100.,200.,500.])
def test_mass_enthalpy_and_duty(h):
    a,b,mix,q=process_water_split(h,0.,100.,1000.)
    assert a>=0 and b>=0
    assert a+b==pytest.approx(10.)
    assert (a*h)/(a+b)==pytest.approx(mix)
    assert a*h==pytest.approx(q)
    assert q<=1000.
    if h>=100.:
        assert mix==100. and q==1000.
    else:
        assert b==0. and mix==h

def test_no_bypass_overdelivery():
    a,b,h,q=process_water_split(200.,0.,100.,1000.,bypass=False)
    assert (a,b,h,q)==(10.,0.,200.,2000.)

def test_conflicting_controller_rejected():
    with pytest.raises(ValueError):
        run_closed_cycle(ClosedCycle(),water_control_gain_kg_s_K=.004,process_duty_W=1000.)

@pytest.mark.parametrize("bypass",[True,False])
def test_full_ledger_and_fixed_process_flow(bypass):
    c=ClosedCycle()
    c=replace(c,charge_s=120.,discharge_s=60.,train=replace(c.train,bed_cells=2,hx_cells=2))
    x=run_closed_cycle(c,reverse_discharge=True,valve_loss_K=2.,process_duty_W=1500.,process_bypass=bypass)
    d=x["discharge"]
    assert d["water_throughput_kg"]==pytest.approx(d["process_demand_flow_kg_s"]*60,abs=1e-6)
    assert d["water_throughput_kg"]==pytest.approx(d["hx_water_throughput_kg"]+d["bypass_water_throughput_kg"])
    assert d["water_boundary_heat_J"]==pytest.approx(1500.*60-d["process_duty_deficit_J"]+d["process_duty_excess_J"],abs=.2)
    assert 0<=d["simultaneous_target_duration_s"]<=60.
    assert d["simultaneous_target_heat_J"]>=-1e-6
    assert abs(x["repeated_sequence_electrical_residual_J"])<.2
    if bypass:
        assert d["process_duty_excess_J"]<1e-6
        assert d["max_water_outlet_C"]<=150.+1e-8
    else:
        assert d["bypass_water_throughput_kg"]==0.
